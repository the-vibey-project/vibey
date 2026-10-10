# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The one client every sovereign provider talks to the local model through.

Ollama's chat API, with `format` either a JSON schema (compiled to a grammar, so
malformed JSON is unreachable) or the string ``"json"`` (JSON mode: well-formed JSON,
any shape). The sovereign DESIGN and DECOMPOSE producers use JSON mode -- a grammar
compiled from their larger schemas stalled GPT-OSS on the reference host -- and validate
the decoded object themselves (`validated_ask.ValidatedAsk`), so a caller asking in JSON
mode gets a JSON object back and nothing more is promised.

Two replies are retried, once each, and never both:

- **Out of output budget.** gpt-oss reasons before it answers, and when the reasoning
  spends the whole `num_predict` Ollama returns ``done_reason == "length"`` with empty
  content and a full `thinking` channel. At temperature 0 the same request fails the
  same way, so the retry asks again with a larger budget (bounded by the context
  ceiling) and lighter reasoning (`VIBEY_OLLAMA_RETRY_THINK`). If that is still cut
  short, `OutputBudgetExhausted` says so -- a CAPACITY failure naming the knobs, not an
  anonymous "empty content".
- **Empty for any other reason** (a grammar the build could not satisfy): one retry in
  JSON mode, as before.

It exists as one class because there are two callers -- the DESIGN provider and the
DECOMPOSE producer -- and the endpoint, the model and the request shape were a private
copy inside the first. Two copies of a hard-coded endpoint is how the second one gets
pointed somewhere the first is not.

The family has no public client to reuse (ADR-0017): `vibey_gh.local_review` makes the
same kind of call, but only through private helpers bound to its own review schema.
This is the general form; that one can converge on it.
"""

import asyncio
import json
import pathlib
import threading
import time
import urllib.parse
import urllib.request
from collections.abc import AsyncGenerator, Callable, Iterator, Mapping
from contextlib import aclosing
from typing import Any
from uuid import uuid4

from vibey.domain.config import ConfigError
from vibey.domain.errors import OutputBudgetExhausted
from vibey.infrastructure.engines.interfaces.ollama_chat_interface import (
    OllamaStreamTransportInterface,
    OllamaTransportInterface,
    WireLogInterface,
)
from vibey.infrastructure.engines.wire_log import WIRE_LOG_ENV, JsonlWireLog, NullWireLog

#: Environment keys, beside their defaults (ADR-0018). `VIBEY_OLLAMA_URL` is the name
#: vibey-gh's local-review fallback already reads, so one setting points both at the
#: same server.
OLLAMA_URL_ENV = "VIBEY_OLLAMA_URL"
OLLAMA_MODEL_ENV = "VIBEY_OLLAMA_MODEL"
OLLAMA_TIMEOUT_ENV = "VIBEY_OLLAMA_TIMEOUT"
OLLAMA_CONTEXT_ENV = "VIBEY_OLLAMA_CONTEXT"
OLLAMA_OUTPUT_ENV = "VIBEY_OLLAMA_OUTPUT"
OLLAMA_FIT_ENV = "VIBEY_OLLAMA_FIT"
OLLAMA_RETRY_THINK_ENV = "VIBEY_OLLAMA_RETRY_THINK"
VIBEY_REVISION_ENV = "VIBEY_REVISION"

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "gpt-oss:20b"
DEFAULT_OLLAMA_TIMEOUT = 900
DEFAULT_OLLAMA_CONTEXT = 8192
DEFAULT_OLLAMA_OUTPUT = 2048
#: The reasoning level asked for on the retry after a reply ran out of output budget.
#: Ollama 0.34 accepts these for gpt-oss, and accepts (then ignores) a level for a model
#: that only thinks on or off; "none" sends no `think` at all, keeping the model default.
DEFAULT_OLLAMA_RETRY_THINK = "low"
THINK_LEVELS: dict[str, str | bool | None] = {
    "low": "low",
    "medium": "medium",
    "high": "high",
    "max": "max",
    "true": True,
    "false": False,
    "none": None,
}

_HTTP_SCHEMES = ("http", "https")


def _load_fit(
    path: str | None, url: str, model: str, revision: str | None
) -> dict[str, int] | None:
    if not path:
        return None
    try:
        record = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        if record.get("url") != url or record.get("model") != model:
            return None
        if revision and record.get("revision") != revision:
            return None
        fit = record.get("selected_fit")
        if not isinstance(fit, dict) or not fit.get("valid"):
            return None
        context = int(fit["context"])
        output = int(fit["output"])
        if context < 4096 or output <= 0:
            return None
        shape = record.get("prompt_shape")
        max_prompt_chars = int(shape["system_chars"]) + int(shape["user_chars"])
        return {"context": context, "output": output, "max_prompt_chars": max_prompt_chars}
    except (OSError, ValueError, TypeError, KeyError):
        return None


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

    async def stream_json(
        self, url: str, payload: Mapping[str, object], *, timeout: int
    ) -> AsyncGenerator[dict[str, object], None]:
        """Each JSON line of a `stream: true` reply, as it arrives.

        The blocking read runs on a worker thread and hands lines to the event loop through
        a queue, so a slow generation still stalls nothing else. `timeout` bounds one read,
        not the answer: a model that keeps producing is never cut off by it."""
        loop = asyncio.get_running_loop()
        lines: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
        stop = threading.Event()

        def pump() -> None:
            try:
                for line in self._read_lines(url, payload, timeout, stop):
                    loop.call_soon_threadsafe(lines.put_nowait, ("line", line))
            except Exception as exc:  # reported to the consumer, never lost on the thread
                loop.call_soon_threadsafe(lines.put_nowait, ("error", exc))
            else:
                loop.call_soon_threadsafe(lines.put_nowait, ("end", None))

        reader = loop.run_in_executor(None, pump)
        try:
            while True:
                kind, value = await lines.get()
                if kind == "line":
                    yield value
                elif kind == "error":
                    raise value
                else:
                    return
        finally:
            stop.set()
            await reader

    def _read_lines(
        self, url: str, payload: Mapping[str, object], timeout: int, stop: threading.Event
    ) -> Iterator[dict[str, object]]:
        if urllib.parse.urlsplit(url).scheme not in _HTTP_SCHEMES:
            raise ValueError(f"refusing a non-HTTP model endpoint: {url!r}")
        request = urllib.request.Request(  # nosec B310 - scheme checked above
            url,
            data=json.dumps(dict(payload)).encode(),
            headers={"Content-Type": "application/json"},
        )
        with self._opener(request, timeout=timeout) as response:
            for raw in response:
                if stop.is_set():
                    return
                text = raw.strip()
                if not text:
                    continue
                line = json.loads(text)
                if not isinstance(line, dict):
                    raise ValueError("Ollama streamed a non-object line")
                yield line


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
    #: How much larger the output budget is on the one retry after a reply was cut short.
    OUTPUT_RETRY_FACTOR = 2

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_OLLAMA_URL,
        model: str = DEFAULT_OLLAMA_MODEL,
        timeout: int = DEFAULT_OLLAMA_TIMEOUT,
        context_ceiling: int = DEFAULT_OLLAMA_CONTEXT,
        output_ceiling: int = DEFAULT_OLLAMA_OUTPUT,
        fit_prompt_chars: int | None = None,
        retry_think: str | bool | None = DEFAULT_OLLAMA_RETRY_THINK,
        transport: OllamaTransportInterface | None = None,
        stream_transport: OllamaStreamTransportInterface | None = None,
        wire_log: WireLogInterface | None = None,
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
        if retry_think not in THINK_LEVELS.values():
            raise ConfigError(
                OLLAMA_RETRY_THINK_ENV,
                f"must be one of {', '.join(THINK_LEVELS)}, got {retry_think!r}",
            )
        self._model = model.strip()
        self._timeout = timeout
        self._context_ceiling = context_ceiling
        self._output_ceiling = output_ceiling
        self._fit_prompt_chars = fit_prompt_chars
        self._retry_think = retry_think
        self._transport = transport if transport is not None else UrllibOllamaTransport()
        # A wire log is the operator asking to watch: only then is the reply streamed, so a
        # run nobody is watching keeps its one blocking request, exactly as before.
        self._streaming = wire_log is not None
        self._wire_log: WireLogInterface = wire_log if wire_log is not None else NullWireLog()
        self._stream_transport: OllamaStreamTransportInterface = (
            stream_transport if stream_transport is not None else UrllibOllamaTransport()
        )

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str],
        *,
        model: str | None = None,
        transport: OllamaTransportInterface | None = None,
        stream_transport: OllamaStreamTransportInterface | None = None,
        wire_log: WireLogInterface | None = None,
    ) -> "OllamaChatClient":
        """Endpoint, model and timeout from the environment, over today's defaults.

        An explicit `model` -- the CLI's `--ollama-model` -- beats `VIBEY_OLLAMA_MODEL`.
        An empty variable counts as unset, the way `${VIBEY_OLLAMA_URL:-...}` treats it
        in the workflows that already read it.
        """
        raw_timeout = environ.get(OLLAMA_TIMEOUT_ENV) or str(DEFAULT_OLLAMA_TIMEOUT)
        raw_context = environ.get(OLLAMA_CONTEXT_ENV) or str(DEFAULT_OLLAMA_CONTEXT)
        raw_output = environ.get(OLLAMA_OUTPUT_ENV) or str(DEFAULT_OLLAMA_OUTPUT)
        fit_path = environ.get(OLLAMA_FIT_ENV)
        fit = _load_fit(
            fit_path,
            environ.get(OLLAMA_URL_ENV) or DEFAULT_OLLAMA_URL,
            model or environ.get(OLLAMA_MODEL_ENV) or DEFAULT_OLLAMA_MODEL,
            environ.get(VIBEY_REVISION_ENV),
        )
        if fit is not None:
            raw_context = str(fit["context"])
            raw_output = str(fit["output"])
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
        raw_think = (environ.get(OLLAMA_RETRY_THINK_ENV) or DEFAULT_OLLAMA_RETRY_THINK).strip()
        if raw_think.lower() not in THINK_LEVELS:
            raise ConfigError(
                OLLAMA_RETRY_THINK_ENV,
                f"must be one of {', '.join(THINK_LEVELS)}, got {raw_think!r}",
            )
        return cls(
            base_url=environ.get(OLLAMA_URL_ENV) or DEFAULT_OLLAMA_URL,
            model=model or environ.get(OLLAMA_MODEL_ENV) or DEFAULT_OLLAMA_MODEL,
            timeout=timeout,
            context_ceiling=context_ceiling,
            output_ceiling=output_ceiling,
            fit_prompt_chars=fit.get("max_prompt_chars") if fit is not None else None,
            retry_think=THINK_LEVELS[raw_think.lower()],
            transport=transport,
            stream_transport=stream_transport,
            wire_log=wire_log if wire_log is not None else cls._wire_log_from(environ),
        )

    @staticmethod
    def _wire_log_from(environ: Mapping[str, str]) -> WireLogInterface | None:
        """The wire log `VIBEY_LLM_WIRE_LOG` names (`-vvv` sets it), or none."""
        path = (environ.get(WIRE_LOG_ENV) or "").strip()
        return JsonlWireLog(pathlib.Path(path).expanduser()) if path else None

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
        call = uuid4().hex[:8]
        bounded_user = self._bounded_user(user)
        prompt_chars = len(system) + len(bounded_user)
        fit_applies = self._fit_prompt_chars is None or prompt_chars <= self._fit_prompt_chars
        context_ceiling = self._context_ceiling if fit_applies else DEFAULT_OLLAMA_CONTEXT
        num_predict = self._output_ceiling if fit_applies else DEFAULT_OLLAMA_OUTPUT
        num_ctx = min(
            context_ceiling,
            max(self.CONTEXT_FLOOR, prompt_chars // self.CHARS_PER_TOKEN + self.CONTEXT_RESERVE),
        )
        endpoint = f"{self._base_url}/api/chat"
        payload = self._payload(
            system, bounded_user, schema, num_ctx, num_predict, stream=self._streaming
        )
        body = await self._post(endpoint, payload, call, 1)
        message = body.get("message")
        if self._cut_short(body):
            # The reasoning spent the budget before the answer began. At temperature 0 the
            # same request fails the same way, so ask once more with room to finish: a
            # larger budget, bounded by the context ceiling, and lighter reasoning.
            prompt_tokens = body.get("prompt_eval_count")
            if not isinstance(prompt_tokens, int) or prompt_tokens <= 0:
                prompt_tokens = prompt_chars // self.CHARS_PER_TOKEN
            num_predict = min(
                num_predict * self.OUTPUT_RETRY_FACTOR,
                max(num_predict, context_ceiling - prompt_tokens),
            )
            num_ctx = min(context_ceiling, max(num_ctx, prompt_tokens + num_predict))
            payload = self._payload(
                system,
                bounded_user,
                schema,
                num_ctx,
                num_predict,
                think=self._retry_think,
                stream=self._streaming,
            )
            body = await self._post(endpoint, payload, call, 2)
            if self._cut_short(body):
                raise OutputBudgetExhausted(
                    self._model, output_tokens=num_predict, context_tokens=num_ctx
                )
            message = body.get("message")
        elif isinstance(message, dict) and message.get("content") == "":
            # Local model builds can emit an empty message when generation is interrupted
            # or grammar compilation cannot satisfy it. One bounded JSON-mode retry keeps
            # the transport live; callers still validate the decoded object.
            payload["format"] = "json"
            body = await self._post(endpoint, payload, call, 2)
            message = body.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise ValueError("Ollama response carried no message content")
        if not message["content"].strip():
            raise ValueError("Ollama response carried empty message content")
        value = json.loads(message["content"])
        # Neither a grammar nor JSON mode is trusted across a process boundary: assert the
        # top-level shape, so a gateway that is not actually Ollama cannot hand back
        # something that is not an answer.
        if not isinstance(value, dict):
            raise ValueError(f"expected a JSON object, got {type(value).__name__}")
        return value

    async def _post(
        self, endpoint: str, payload: Mapping[str, object], call: str, attempt: int
    ) -> dict[str, object]:
        """One request, recorded on the wire log whichever way it ends."""
        started = time.monotonic()
        self._wire_log.request(call, attempt, endpoint, payload)
        try:
            if self._streaming:
                body = await self._streamed_body(endpoint, payload, call, attempt)
            else:
                body = await self._transport.post_json(endpoint, payload, timeout=self._timeout)
        except Exception as exc:
            self._wire_log.error(call, attempt, exc, time.monotonic() - started)
            raise
        self._wire_log.response(call, attempt, body, time.monotonic() - started)
        return body

    async def _streamed_body(
        self, endpoint: str, payload: Mapping[str, object], call: str, attempt: int
    ) -> dict[str, object]:
        """A `stream: true` reply put back together as the one body `stream: false` returns:
        the final line's counts and timings, with the message the chunks spelled out."""
        content: list[str] = []
        thinking: list[str] = []
        final: dict[str, object] | None = None
        async with aclosing(
            self._stream_transport.stream_json(endpoint, payload, timeout=self._timeout)
        ) as lines:
            async for line in lines:
                if "error" in line:
                    raise ValueError(f"Ollama stream error: {line['error']}")
                message = line.get("message")
                if isinstance(message, dict):
                    said = message.get("content")
                    reasoned = message.get("thinking")
                    said = said if isinstance(said, str) else ""
                    reasoned = reasoned if isinstance(reasoned, str) else ""
                    if said or reasoned:
                        content.append(said)
                        thinking.append(reasoned)
                        self._wire_log.chunk(call, attempt, content=said, thinking=reasoned)
                if line.get("done") is True:
                    final = line
                    break
        if final is None:
            raise ValueError("Ollama stream ended before the answer was complete")
        body = {key: value for key, value in final.items() if key != "message"}
        assembled: dict[str, object] = {"role": "assistant", "content": "".join(content)}
        if any(thinking):
            assembled["thinking"] = "".join(thinking)
        body["message"] = assembled
        return body

    def _payload(
        self,
        system: str,
        user: str,
        schema: Mapping[str, object] | str,
        num_ctx: int,
        num_predict: int,
        *,
        think: str | bool | None = None,
        stream: bool = False,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            # A schema is compiled to a grammar; "json" asks only for well-formed JSON.
            "format": dict(schema) if isinstance(schema, Mapping) else schema,
            "stream": stream,
            # temperature 0 because an answer that changes on unchanged input cannot be
            # reasoned about by the phase that consumes it.
            "options": {"temperature": 0, "num_ctx": num_ctx, "num_predict": num_predict},
        }
        if think is not None:
            payload["think"] = think
        return payload

    @staticmethod
    def _cut_short(body: Mapping[str, object]) -> bool:
        """Generation stopped at the output limit before a whole JSON answer was written.

        Only `done_reason == "length"` counts: an empty reply that stopped for another
        reason is not a budget problem, and more budget would not help it.
        """
        if body.get("done_reason") != "length":
            return False
        message = body.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            return True
        try:
            json.loads(content)
        except ValueError:
            return True
        return False

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
