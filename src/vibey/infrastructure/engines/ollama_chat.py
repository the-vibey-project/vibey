# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The one client every sovereign provider talks to the local model through.

Ollama's chat API with the answer's JSON schema passed as `format`. Ollama compiles the
schema to a grammar and zeroes the probability of any token that would break it, so
malformed JSON is not reachable: the boundary needs no fence-hunting and no repair pass
(ADR-0027).

It exists as one class because there are now two callers -- the DESIGN provider and the
DECOMPOSE producer -- and the endpoint, the model and the request shape were a private
copy inside the first. Two copies of a hard-coded endpoint is how the second one gets
pointed somewhere the first is not.

The family has no public client to reuse (ADR-0017): `vibey_gh.local_review` makes the
same kind of call, but only through private helpers bound to its own review schema.
This is the general form; that one can converge on it.
"""

import asyncio
import json
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any

from vibey.domain.config import ConfigError
from vibey.infrastructure.engines.interfaces.ollama_chat_interface import (
    OllamaTransportInterface,
)

#: Environment keys, beside their defaults (ADR-0018). `VIBEY_OLLAMA_URL` is the name
#: vibey-gh's local-review fallback already reads, so one setting points both at the
#: same server.
OLLAMA_URL_ENV = "VIBEY_OLLAMA_URL"
OLLAMA_MODEL_ENV = "VIBEY_OLLAMA_MODEL"
OLLAMA_TIMEOUT_ENV = "VIBEY_OLLAMA_TIMEOUT"
OLLAMA_CONTEXT_ENV = "VIBEY_OLLAMA_CONTEXT"
OLLAMA_OUTPUT_ENV = "VIBEY_OLLAMA_OUTPUT"

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "gpt-oss:20b"
DEFAULT_OLLAMA_TIMEOUT = 900
DEFAULT_OLLAMA_CONTEXT = 8192
DEFAULT_OLLAMA_OUTPUT = 2048

_HTTP_SCHEMES = ("http", "https")


class UrllibOllamaTransport:
    """Blocking `urllib`, kept off the event loop, and only ever over HTTP(S)."""

    def __init__(self, *, opener: Callable[..., Any] = urllib.request.urlopen) -> None:
        # The opener is a seam, not a setting: tests hand in a double instead of
        # patching `urllib` (ADR-0016).
        self._opener = opener

    async def post_json(
        self, url: str, payload: Mapping[str, object], *, timeout: int
    ) -> dict[str, object]:
        # A slow local generation must not stall the conductor's other work.
        return await asyncio.to_thread(self._send, url, payload, timeout)

    def _send(self, url: str, payload: Mapping[str, object], timeout: int) -> dict[str, object]:
        # `urlopen` also speaks file:, ftp: and data:. The client already refuses such a
        # base URL at construction; this is the same check at the point of use, so the
        # transport is safe on its own and not only behind that client.
        if urllib.parse.urlsplit(url).scheme not in _HTTP_SCHEMES:
            raise ValueError(f"refusing a non-HTTP model endpoint: {url!r}")
        request = urllib.request.Request(  # nosec B310 - scheme checked above
            url,
            data=json.dumps(dict(payload)).encode(),
            headers={"Content-Type": "application/json"},
        )
        with self._opener(request, timeout=timeout) as response:
            result = json.loads(response.read())
        if not isinstance(result, dict):
            raise ValueError("Ollama returned a non-object response")
        return result


class OllamaChatClient:
    """One schema-constrained question to one model on one Ollama server."""

    #: Ollama's default context window is far smaller than a full ledger or spec, and
    #: overflowing it degrades generation from seconds to never-finishes rather than
    #: erroring. Code tokenises near 3 characters per token; the reserve covers the
    #: schema and the answer; the ceiling makes an enormous request fail visibly rather
    #: than exhaust the host.
    CONTEXT_FLOOR = 4096
    CONTEXT_CEILING = 32768
    CONTEXT_RESERVE = 2048
    CHARS_PER_TOKEN = 3

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_OLLAMA_URL,
        model: str = DEFAULT_OLLAMA_MODEL,
        timeout: int = DEFAULT_OLLAMA_TIMEOUT,
        context_ceiling: int = DEFAULT_OLLAMA_CONTEXT,
        output_ceiling: int = DEFAULT_OLLAMA_OUTPUT,
        transport: OllamaTransportInterface | None = None,
    ) -> None:
        self._base_url = self._validated_base_url(base_url)
        if not model.strip():
            raise ConfigError(OLLAMA_MODEL_ENV, "the local model name is empty")
        if timeout <= 0:
            raise ConfigError(OLLAMA_TIMEOUT_ENV, f"must be a positive number, got {timeout}")
        if context_ceiling < self.CONTEXT_FLOOR:
            raise ConfigError(
                OLLAMA_CONTEXT_ENV,
                f"must be at least {self.CONTEXT_FLOOR}, got {context_ceiling}",
            )
        if output_ceiling <= 0:
            raise ConfigError(OLLAMA_OUTPUT_ENV, f"must be positive, got {output_ceiling}")
        self._model = model.strip()
        self._timeout = timeout
        self._context_ceiling = context_ceiling
        self._output_ceiling = output_ceiling
        self._transport = transport if transport is not None else UrllibOllamaTransport()

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str],
        *,
        model: str | None = None,
        transport: OllamaTransportInterface | None = None,
    ) -> "OllamaChatClient":
        """Endpoint, model and timeout from the environment, over today's defaults.

        An explicit `model` -- the CLI's `--ollama-model` -- beats `VIBEY_OLLAMA_MODEL`.
        An empty variable counts as unset, the way `${VIBEY_OLLAMA_URL:-...}` treats it
        in the workflows that already read it.
        """
        raw_timeout = environ.get(OLLAMA_TIMEOUT_ENV) or str(DEFAULT_OLLAMA_TIMEOUT)
        raw_context = environ.get(OLLAMA_CONTEXT_ENV) or str(DEFAULT_OLLAMA_CONTEXT)
        raw_output = environ.get(OLLAMA_OUTPUT_ENV) or str(DEFAULT_OLLAMA_OUTPUT)
        try:
            timeout = int(raw_timeout)
        except ValueError as exc:
            raise ConfigError(
                OLLAMA_TIMEOUT_ENV, f"must be a whole number of seconds, got {raw_timeout!r}"
            ) from exc
        try:
            context_ceiling = int(raw_context)
        except ValueError as exc:
            raise ConfigError(
                OLLAMA_CONTEXT_ENV,
                f"must be a whole number of tokens, got {raw_context!r}",
            ) from exc
        try:
            output_ceiling = int(raw_output)
        except ValueError as exc:
            raise ConfigError(
                OLLAMA_OUTPUT_ENV,
                f"must be a whole number of tokens, got {raw_output!r}",
            ) from exc
        return cls(
            base_url=environ.get(OLLAMA_URL_ENV) or DEFAULT_OLLAMA_URL,
            model=model or environ.get(OLLAMA_MODEL_ENV) or DEFAULT_OLLAMA_MODEL,
            timeout=timeout,
            context_ceiling=context_ceiling,
            output_ceiling=output_ceiling,
            transport=transport,
        )

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def model(self) -> str:
        return self._model

    def context_window(self, prompt_chars: int) -> int:
        wanted = prompt_chars // self.CHARS_PER_TOKEN + self.CONTEXT_RESERVE
        return min(self._context_ceiling, max(self.CONTEXT_FLOOR, wanted))

    def _bounded_user(self, user: str) -> str:
        budget = (self._context_ceiling - self.CONTEXT_RESERVE) * self.CHARS_PER_TOKEN
        if len(user) <= budget:
            return user
        head = budget * 2 // 3
        tail = budget - head
        return (
            user[:head]
            + "\n\n[context elided by sovereign client: middle omitted]\n\n"
            + user[-tail:]
        )

    async def ask(
        self, system: str, user: str, schema: Mapping[str, object] | str
    ) -> dict[str, object]:
        bounded_user = self._bounded_user(user)
        payload: dict[str, object] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": bounded_user},
            ],
            # The grammar. Malformed JSON is unreachable, so this boundary needs no
            # fence-hunting and no repair pass.
            "format": dict(schema) if isinstance(schema, Mapping) else schema,
            "stream": False,
            # temperature 0 because an answer that changes on unchanged input cannot be
            # reasoned about by the phase that consumes it.
            "options": {
                "temperature": 0,
                "num_ctx": self.context_window(len(system) + len(bounded_user)),
                "num_predict": self._output_ceiling,
            },
        }
        endpoint = f"{self._base_url}/api/chat"
        body = await self._transport.post_json(endpoint, payload, timeout=self._timeout)
        message = body.get("message")
        if isinstance(message, dict) and message.get("content") == "":
            # Local model builds can emit an empty message when generation is interrupted
            # or grammar compilation cannot satisfy it. One bounded JSON-mode retry keeps
            # the transport live; callers still validate the decoded object.
            payload["format"] = "json"
            body = await self._transport.post_json(endpoint, payload, timeout=self._timeout)
            message = body.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise ValueError("Ollama response carried no message content")
        if not message["content"].strip():
            raise ValueError("Ollama response carried empty message content")
        value = json.loads(message["content"])
        # Constrained decoding guarantees the schema, but this is a boundary with an
        # external process: assert the top-level shape rather than trust it, so a gateway
        # that is not actually Ollama cannot hand back something that is not an answer.
        if not isinstance(value, dict):
            raise ValueError(f"expected a JSON object, got {type(value).__name__}")
        return value

    @staticmethod
    def _validated_base_url(base_url: str) -> str:
        cleaned = base_url.strip().rstrip("/")
        parts = urllib.parse.urlsplit(cleaned)
        if parts.scheme not in _HTTP_SCHEMES or not parts.netloc:
            # The value is never echoed: a URL can carry `user:token@`, and this message
            # reaches a terminal, a log and a CI transcript.
            raise ConfigError(
                OLLAMA_URL_ENV,
                "the local model endpoint must be an http(s) URL with a host "
                "(the value is not shown: a URL can carry credentials)",
            )
        return cleaned
